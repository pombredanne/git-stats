# -*- coding: utf-8 -*-
"""
    Merge one git branch to another and optionally push to origin
"""
from __future__ import division, print_function
from git_calls import *


def report_failure(msg):
    """Each application will replace this with its own reporter
    """
    print('!' * 80, file=sys.stderr)
    print(msg, file=sys.stderr)
    print('@' * 80, file=sys.stderr)


def check_error(condition, msg):
    """If `condition` is True then report error message `msg` to `report_failure` and exit.
    """
    if not condition:
        report_failure(msg)
    assert condition, msg


def checkout_update_branch(branch):
    """Checkout `branch` and update it to match origin
    """
    exec_result = git_checkout(branch, force=True)
    check_error(exec_result.ret == 0, format_error(exec_result))

    # Clean up unpushed commits etc in our working copy
    git_reset('origin/%s' % branch)
    check_error(exec_result.ret == 0, format_error(exec_result))

    conflicts, out_lines, exec_result = git_pull(branch)
    check_error(exec_result.ret == 0, format_error(exec_result, failure='\n'.join(conflicts)))


def merge_branches(whence, whither, do_push, clean_branches, debugging):
    """Merge git branch `whence` to git branch `whither`.
        If `clean_branches` is True then delete all local branches that don't have matching
        remote branches.

        This function is a sequence of git commands.
        If any git command fails then that failure is reported and this script exits with exit code
        -1

    """
    print('=' * 80)
    print(__doc__)
    print('=' * 80)
    print('merge_branches: "%s" -> "%s"' % (whence, whither))

    git_debugging(debugging)

    # Prevent git from choking on diffs that have many file renames
    exec_result = git_config_set('merge.renameLimit', '999999')
    check_error(exec_result.ret == 0, format_error(exec_result))

    # Clean up partial commits etc in our working copy
    git_reset('HEAD')
    check_error(exec_result.ret == 0, format_error(exec_result))

    # Fetch any branches that are not already local
    exec_result = git_fetch()
    check_error(exec_result.ret == 0, format_error(exec_result))

    # Make our sandbox tracks all branches in origin
    branch_list, exec_result = git_track_all(clean_branches)

    check_error(whence and whither, 'to and from branches required: from="%s",to="%s"' %
                (whence, whither))

    # We can only merge to and from branches that exist
    check_error(whither in branch_list,
                'To branch "%s" not in branches\n%s' % (whither, '\n'.join(sorted(branch_list))))
    check_error(whence in branch_list,
                'From branch "%s" not in branches\n%s' % (whence, '\n'.join(sorted(branch_list))))

    #
    # fetch (above), checkout and pull to make working directory match origin latest
    #
    # exec_result = git_fetch()
    # check_error(exec_result.ret == 0, format_error(exec_result))

    # Update `whence` and `whither` and leave `whither` checked out
    checkout_update_branch(whence)
    checkout_update_branch(whither)

    # sha_before is SHA-1 hash of origin `whither` before merge
    sha_before, exec_result = git_show_sha()
    check_error(exec_result.ret == 0, format_error(exec_result))

    # Do the merge!
    conflicts, out_lines, exec_result = git_merge(whence)
    check_error(exec_result.ret == 0, format_error(exec_result, failure='\n'.join(conflicts)))

    # sha_after is SHA-1 hash of origin `whither` after merge
    sha_after, exec_result = git_show_sha()
    check_error(exec_result.ret == 0, format_error(exec_result))

    #
    # If we get here then the merge has succeeded.
    # We print the git log message of the change if there was one.
    #
    print(',' * 80)
    print('sha_before=%s' % sha_before)
    print('sha_after =%s' % sha_after)
    print('-' * 80)
    if sha_before == sha_after:
        print('No change')
    else:
        exec_result = git_show()
        print(exec_result.out)
    print('=' * 80)

    # Do the push. Be careful!
    if do_push:
        assert False
        exec_result = git_push(whither)
        check_error(exec_result.ret == 0, format_error(exec_result))

    # exec_result = git_config_unset('merge.renameLimit')
    # check_error(exec_result.ret == 0, format_error(exec_result))


def merge_up(branch_list, do_push, clean_branches, debugging):
    """Merge branches in `branch_list` "up" i.e. from first element to last
        e.g. for brach_list = [b, b2, b3]
             merge b1 -> b2 then
             merge b2 -> b3

        Terminate on first failure
    """
    print('Merging:\n%s' % ' ->\n'.join('%4d: "%s"' % (i, b) for i, b in enumerate(branch_list)))

    merge_list = list(zip(branch_list[:-1], branch_list[1:]))
    print('Planned merges:\n%s' %
          '\n'.join('%4d: "%s" -> "%s"' % (i, b1, b2) for i, (b1, b2) in enumerate(merge_list)))

    for i, (b1, b2) in enumerate(zip(branch_list[:-1], branch_list[1:])):
        merge_branches(b1, b2, do_push, clean_branches, debugging)


def main():
    import optparse

    lowpriority()

    parser = optparse.OptionParser('python ' + sys.argv[0] + ' [options] [<directory>]')
    parser.add_option('-d', '--debug', action='store_true', default=False, dest='debugging',
                      help='Show debug messages')
    parser.add_option('-p', '--push', action='store_true', default=False, dest='do_push',
                      help='Push commit to origin')
    parser.add_option('-c', '--clean-branches', action='store_true', default=False,
                      dest='clean_branches',
                      help='Clean out pre-existing local branches')
    parser.add_option('-t', '--to', dest='whither', default='',
                      help='Branch to merge to')
    parser.add_option('-f', '--from', dest='whence', default='',
                      help='Branch to merge from')
    parser.add_option('-u', '--up', dest='branch_list_str', default='',
                      help='Branch to merge to')

    options, _ = parser.parse_args()

    if options.branch_list_str:
        assert not (options.whence or options.whither), '--up cannot be used with --to and --from'
        branch_list = options.branch_list_str.split()
        merge_up(branch_list, options.do_push, options.clean_branches, options.debugging)
    else:
        merge_branches(options.whence, options.whither, options.do_push, options.clean_branches,
                       options.debugging)


if __name__ == '__main__':

    main()
    print()
